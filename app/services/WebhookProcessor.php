<?php

class WebhookProcessor
{
    private PDO $db;
    private EvolutionClient $evolution;
    private AIService $ai;

    public function __construct(PDO $db, EvolutionClient $evolution, AIService $ai)
    {
        $this->db = $db;
        $this->evolution = $evolution;
        $this->ai = $ai;
    }

    public function handle(array $payload): array
    {
        $event = (string) ($payload['event'] ?? '');
        $data = is_array($payload['data'] ?? null) ? $payload['data'] : [];
        $key = is_array($data['key'] ?? null) ? $data['key'] : [];
        $fromMe = (bool) ($key['fromMe'] ?? false);

        if (!in_array($event, ['messages.upsert', 'MESSAGES_UPSERT'], true)) {
            return ['status' => 'ignored', 'reason' => 'event_not_supported'];
        }
        if ($fromMe) {
            return ['status' => 'ignored', 'reason' => 'outgoing_message'];
        }

        $senderPhone = normalize_phone((string) ($key['remoteJid'] ?? ''));
        if (!$senderPhone || $senderPhone === 'status') {
            return ['status' => 'ignored', 'reason' => 'invalid_sender'];
        }

        $message = is_array($data['message'] ?? null) ? $data['message'] : [];
        [$text, $images] = $this->extractContent($message, $data, false);
        $messageId = (string) ($key['id'] ?? '');

        $admin = $this->findAdmin($senderPhone);
        $whatsappMessageId = $this->saveWhatsappMessage($payload, $senderPhone, $messageId, $text, $images, (bool) $admin);

        if (!$admin) {
            app_log('info', 'Ignoring WhatsApp message from non-admin', ['phone' => $senderPhone]);
            return ['status' => 'ignored', 'reason' => 'sender_not_admin'];
        }

        $pendingOffer = $this->findPendingOffer((int) $admin['id']);
        if ($pendingOffer && count($images) === 0 && $text !== '') {
            $result = $this->handleAdminReply($pendingOffer, $admin, $senderPhone, $text);
            $this->markMessageProcessed($whatsappMessageId);
            return $result;
        }

        if (count($images) > 0) {
            $this->evolution->sendText(
                $senderPhone,
                "Oferta recebida. Estou analisando as informacoes e preparando o anuncio para aprovacao."
            );
        }

        return [
            'status' => 'queued',
            'message_id' => $whatsappMessageId,
            'note' => 'Mensagem aceita. O cron process_pending.php prepara a previa para aprovacao.',
        ];
    }

    public function processPending(int $waitSeconds = 45): array
    {
        $stmt = $this->db->query(
            'SELECT * FROM whatsapp_messages
             WHERE status = "accepted" AND processed_at IS NULL
             ORDER BY sender_phone, id'
        );
        $groups = [];
        foreach ($stmt->fetchAll() as $row) {
            $groups[$row['sender_phone']][] = $row;
        }

        $processed = [];
        foreach ($groups as $phone => $rows) {
            $last = end($rows);
            $lastTime = strtotime((string) $last['created_at']) ?: time();
            if ((time() - $lastTime) < $waitSeconds) {
                continue;
            }
            $processed[] = $this->processMessageGroup((string) $phone, $rows);
        }

        return ['processed_groups' => $processed];
    }

    private function processMessageGroup(string $senderPhone, array $rows): array
    {
        $admin = $this->findAdmin($senderPhone);
        if (!$admin) {
            $this->markMessagesProcessed($rows);
            return ['phone' => $senderPhone, 'status' => 'ignored', 'reason' => 'admin_not_found'];
        }

        $texts = [];
        $images = [];
        $firstMessageId = (int) $rows[0]['id'];
        foreach ($rows as $row) {
            $payload = json_decode((string) $row['raw_payload'], true);
            if (!is_array($payload)) {
                continue;
            }
            $data = is_array($payload['data'] ?? null) ? $payload['data'] : [];
            $message = is_array($data['message'] ?? null) ? $data['message'] : [];
            [$text, $rowImages] = $this->extractContent($message, $data);
            if ($text) {
                $texts[] = $text;
            }
            foreach ($rowImages as $image) {
                $images[] = $image;
            }
        }

        $text = trim(implode("\n\n", array_unique(array_filter($texts))));
        if (!$text || count($images) === 0) {
            $this->markMessagesProcessed($rows);
            return ['phone' => $senderPhone, 'status' => 'ignored', 'reason' => 'missing_text_or_image'];
        }

        $offerId = $this->createOffer((int) $admin['id'], $firstMessageId, $text);
        $this->saveOfferImages($offerId, $images);
        $this->setOfferStatus($offerId, 'em_analise_ia');

        $aiResult = $this->ai->padronizarDescricao($text, [
            'offer_id' => $offerId,
            'user_id' => (int) $admin['id'],
            'origin' => 'webhook:evolution',
        ]);
        if (!$aiResult['success']) {
            $this->markOfferError($offerId, 'em_analise_ia', (string) ($aiResult['error'] ?? 'Erro na IA'));
            $this->markMessagesProcessed($rows);
            $this->evolution->sendText($senderPhone, 'Nao consegui preparar a previa do anuncio. Verifique os logs do AIService.');
            return ['status' => 'error', 'reason' => 'ai_failed', 'offer_id' => $offerId];
        }

        $this->markOfferForApproval($offerId, (string) $aiResult['title'], (string) $aiResult['description'], (string) $aiResult['final_message'], 'aguardando_aprovacao');
        $this->saveOfferVersion($offerId, (int) $admin['id'], (string) $aiResult['title'], (string) $aiResult['description'], (string) $aiResult['final_message'], '', 'ia');
        $this->sendApprovalPreview($senderPhone, $offerId);
        $this->markMessagesProcessed($rows);

        return ['status' => 'awaiting_approval', 'offer_id' => $offerId];
    }

    private function handleAdminReply(array $offer, array $admin, string $adminPhone, string $text): array
    {
        $answer = trim($text);
        $status = (string) $offer['status'];

        if ($status === 'reprovada_para_correcao') {
            return $this->correctOffer($offer, $admin, $adminPhone, $answer);
        }

        if (in_array($status, ['aguardando_aprovacao', 'corrigida_pela_ia'], true)) {
            if ($answer === '1') {
                return $this->approveAndSend($offer, $adminPhone);
            }
            if ($answer === '2') {
                $this->setOfferStatus((int) $offer['id'], 'reprovada_para_correcao');
                $this->evolution->sendText($adminPhone, 'Informe o motivo da reprovacao ou o que deseja corrigir no anuncio.');
                return ['status' => 'correction_requested', 'offer_id' => (int) $offer['id']];
            }
            if ($answer === '3') {
                $this->cancelOffer((int) $offer['id']);
                $this->evolution->sendText($adminPhone, "Anuncio cancelado. Nenhuma mensagem foi enviada aos compradores.");
                return ['status' => 'cancelled', 'offer_id' => (int) $offer['id']];
            }

            $this->sendValidOptions($adminPhone);
            return ['status' => 'invalid_option', 'offer_id' => (int) $offer['id']];
        }

        return ['status' => 'ignored', 'reason' => 'no_action_for_status', 'offer_status' => $status];
    }

    private function correctOffer(array $offer, array $admin, string $adminPhone, string $feedback): array
    {
        if ($feedback === '') {
            $this->evolution->sendText($adminPhone, 'Informe o motivo da reprovacao ou o que deseja corrigir no anuncio.');
            return ['status' => 'missing_feedback', 'offer_id' => (int) $offer['id']];
        }

        $offerId = (int) $offer['id'];
        $this->setOfferStatus($offerId, 'em_analise_ia');
        $stmt = $this->db->prepare('UPDATE offers SET correction_feedback = ?, updated_at = NOW() WHERE id = ?');
        $stmt->execute([$feedback, $offerId]);

        $aiResult = $this->ai->corrigirAnuncio((string) ($offer['final_text'] ?? ''), $feedback, [
            'offer_id' => $offerId,
            'user_id' => (int) $admin['id'],
            'origin' => 'webhook:evolution:correction',
        ]);

        if (!$aiResult['success']) {
            $this->markOfferError($offerId, 'reprovada_para_correcao', (string) ($aiResult['error'] ?? 'Erro na IA'));
            $this->evolution->sendText($adminPhone, 'Nao consegui corrigir o anuncio pela IA. Envie outro ajuste ou verifique os logs.');
            return ['status' => 'error', 'reason' => 'ai_correction_failed', 'offer_id' => $offerId];
        }

        $this->markOfferForApproval($offerId, (string) $aiResult['title'], (string) $aiResult['description'], (string) $aiResult['final_message'], 'corrigida_pela_ia');
        $this->saveOfferVersion($offerId, (int) $admin['id'], (string) $aiResult['title'], (string) $aiResult['description'], (string) $aiResult['final_message'], $feedback, 'correcao_ia');
        $this->sendApprovalPreview($adminPhone, $offerId);

        return ['status' => 'awaiting_approval', 'offer_id' => $offerId];
    }

    private function approveAndSend(array $offer, string $adminPhone): array
    {
        $offerId = (int) $offer['id'];
        $this->markOfferApproved($offerId);
        $this->setOfferStatus($offerId, 'em_envio');

        $images = $this->offerImages($offerId);
        $buyers = $this->activeBuyersWithoutDuplicates();
        $result = $this->sendToBuyers($offerId, $buyers, $images, (string) $offer['final_text']);

        $finalStatus = 'enviada';
        if ($result['success'] === 0 && $result['total'] > 0) {
            $finalStatus = 'falha_envio';
        } elseif ($result['failures'] > 0) {
            $finalStatus = 'envio_parcial';
        }
        $this->markOfferSent($offerId, $result['success'], $finalStatus);
        $this->sendAdminSummary($adminPhone, $result);

        return ['status' => 'sent', 'offer_id' => $offerId, 'summary' => $result];
    }

    private function sendApprovalPreview(string $adminPhone, int $offerId): void
    {
        $offer = $this->findOffer($offerId);
        if (!$offer) {
            return;
        }
        $options = "Responda apenas uma opcao:\n\n1 - Aprovar envio\n2 - Reprovar e corrigir\n3 - Cancelar anuncio";
        $caption = trim((string) $offer['final_text']) . "\n\n" . $options;
        $images = $this->offerImages($offerId);
        if (!$images) {
            $this->evolution->sendText($adminPhone, $caption);
            return;
        }
        foreach ($images as $index => $image) {
            $result = $this->evolution->sendMedia(
                $adminPhone,
                (string) $image['media'],
                $index === 0 ? $caption : '',
                (string) $image['mimetype']
            );
            if (!$result['success']) {
                app_log('error', 'Failed to send approval preview to admin', ['offer_id' => $offerId, 'error' => $result['error'] ?? '']);
            }
        }
        $this->evolution->sendText($adminPhone, "Previa do anuncio #" . $offerId . "\n\n" . trim((string) $offer['final_text']) . "\n\n" . $options);
    }

    private function sendValidOptions(string $adminPhone): void
    {
        $this->evolution->sendText($adminPhone, "Opcao invalida. Responda apenas:\n\n1 - Aprovar envio\n2 - Reprovar e corrigir\n3 - Cancelar anuncio");
    }

    private function sendAdminSummary(string $adminPhone, array $summary): void
    {
        $message = "Envio finalizado.\n\nTotal de compradores: " . $summary['total'] . "\nEnviados com sucesso: " . $summary['success'] . "\nFalhas: " . $summary['failures'];
        if ($summary['failure_details']) {
            $message .= "\n\nFalhas:";
            foreach ($summary['failure_details'] as $failure) {
                $message .= "\n- " . $failure['phone'] . ': ' . $failure['error'];
            }
        }
        $this->evolution->sendText($adminPhone, $message);
    }

    private function markMessagesProcessed(array $rows): void
    {
        $ids = array_map(static fn ($row) => (int) $row['id'], $rows);
        if (!$ids) {
            return;
        }
        $placeholders = implode(',', array_fill(0, count($ids), '?'));
        $stmt = $this->db->prepare("UPDATE whatsapp_messages SET processed_at = NOW() WHERE id IN ($placeholders)");
        $stmt->execute($ids);
    }

    private function markMessageProcessed(int $id): void
    {
        $stmt = $this->db->prepare('UPDATE whatsapp_messages SET processed_at = NOW() WHERE id = ?');
        $stmt->execute([$id]);
    }

    private function extractContent(array $message, array $fullData, bool $decodeMedia = true): array
    {
        $text = '';
        $images = [];

        if (!empty($message['conversation'])) {
            $text = (string) $message['conversation'];
        } elseif (isset($message['extendedTextMessage'])) {
            $text = (string) ($message['extendedTextMessage']['text'] ?? '');
        }

        if (isset($message['imageMessage']) && is_array($message['imageMessage'])) {
            $image = $message['imageMessage'];
            $caption = (string) ($image['caption'] ?? '');
            if ($caption && !$text) {
                $text = $caption;
            }
            $decoded = $decodeMedia
                ? $this->evolution->getBase64FromMediaMessage($fullData)
                : ['success' => false, 'error' => 'Imagem ainda nao decodificada'];
            $images[] = [
                'base64' => $decoded['success'] ? (string) ($decoded['base64'] ?? '') : '',
                'url' => (string) ($image['url'] ?? ''),
                'mimetype' => $decoded['success'] ? (string) ($decoded['mimetype'] ?? 'image/jpeg') : (string) ($image['mimetype'] ?? 'image/jpeg'),
                'error' => $decoded['success'] ? '' : (string) ($decoded['error'] ?? 'Falha ao decodificar imagem'),
            ];
        }

        return [trim($text), $images];
    }

    private function findAdmin(string $phone): ?array
    {
        $stmt = $this->db->prepare('SELECT * FROM admins WHERE active = 1');
        $stmt->execute();
        foreach ($stmt->fetchAll() as $admin) {
            if (normalize_phone((string) $admin['phone']) === $phone) {
                return $admin;
            }
        }
        return null;
    }

    private function findPendingOffer(int $adminId): ?array
    {
        $stmt = $this->db->prepare(
            'SELECT * FROM offers
             WHERE admin_id = ? AND status IN ("aguardando_aprovacao", "corrigida_pela_ia", "reprovada_para_correcao")
             ORDER BY id DESC LIMIT 1'
        );
        $stmt->execute([$adminId]);
        $row = $stmt->fetch();
        return $row ?: null;
    }

    private function findOffer(int $offerId): ?array
    {
        $stmt = $this->db->prepare('SELECT * FROM offers WHERE id = ? LIMIT 1');
        $stmt->execute([$offerId]);
        $row = $stmt->fetch();
        return $row ?: null;
    }

    private function saveWhatsappMessage(array $payload, string $phone, string $messageId, string $text, array $images, bool $isAdmin): int
    {
        $stmt = $this->db->prepare(
            'INSERT INTO whatsapp_messages
             (event_id, sender_phone, sender_name, message_type, text_content, raw_payload, is_admin, status, created_at)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, NOW())'
        );
        $stmt->execute([
            $messageId,
            $phone,
            (string) ($payload['data']['pushName'] ?? ''),
            count($images) ? 'image' : 'text',
            $text,
            json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES),
            $isAdmin ? 1 : 0,
            $isAdmin ? 'accepted' : 'ignored',
        ]);
        return (int) $this->db->lastInsertId();
    }

    private function createOffer(int $adminId, int $whatsappMessageId, string $text): int
    {
        $stmt = $this->db->prepare(
            'INSERT INTO offers (admin_id, whatsapp_message_id, original_text, status, created_at)
             VALUES (?, ?, ?, "recebida", NOW())'
        );
        $stmt->execute([$adminId, $whatsappMessageId, $text]);
        return (int) $this->db->lastInsertId();
    }

    private function saveOfferImages(int $offerId, array $images): void
    {
        foreach ($images as $index => $image) {
            $stmt = $this->db->prepare(
                'INSERT INTO offer_images (offer_id, image_url, image_base64, mimetype, position, decode_error, created_at)
                 VALUES (?, ?, ?, ?, ?, ?, NOW())'
            );
            $stmt->execute([
                $offerId,
                $image['url'] ?? '',
                $image['base64'] ?? '',
                $image['mimetype'] ?? 'image/jpeg',
                $index + 1,
                $image['error'] ?? '',
            ]);
        }
    }

    private function offerImages(int $offerId): array
    {
        $stmt = $this->db->prepare('SELECT * FROM offer_images WHERE offer_id = ? ORDER BY position, id');
        $stmt->execute([$offerId]);
        $images = [];
        foreach ($stmt->fetchAll() as $image) {
            $images[] = [
                'id' => (int) $image['id'],
                'media' => (string) ($image['image_base64'] ?: $image['image_url']),
                'mimetype' => (string) ($image['mimetype'] ?: 'image/jpeg'),
            ];
        }
        return $images;
    }

    private function setOfferStatus(int $offerId, string $status): void
    {
        $stmt = $this->db->prepare('UPDATE offers SET status = ?, updated_at = NOW() WHERE id = ?');
        $stmt->execute([$status, $offerId]);
    }

    private function markOfferError(int $offerId, string $status, string $error): void
    {
        $stmt = $this->db->prepare('UPDATE offers SET status = ?, error_message = ?, updated_at = NOW() WHERE id = ?');
        $stmt->execute([$status, $error, $offerId]);
    }

    private function markOfferForApproval(int $offerId, string $title, string $description, string $finalMessage, string $status): void
    {
        $stmt = $this->db->prepare(
            'UPDATE offers SET title = ?, description = ?, final_text = ?, status = ?, error_message = NULL, updated_at = NOW() WHERE id = ?'
        );
        $stmt->execute([$title, $description, $finalMessage, $status, $offerId]);
    }

    private function markOfferApproved(int $offerId): void
    {
        $stmt = $this->db->prepare('UPDATE offers SET status = "aprovada", approved_at = NOW(), updated_at = NOW() WHERE id = ?');
        $stmt->execute([$offerId]);
    }

    private function markOfferSent(int $offerId, int $successCount, string $status): void
    {
        $stmt = $this->db->prepare(
            'UPDATE offers SET status = ?, sent_count = ?, sent_at = NOW(), updated_at = NOW() WHERE id = ?'
        );
        $stmt->execute([$status, $successCount, $offerId]);
    }

    private function cancelOffer(int $offerId): void
    {
        $stmt = $this->db->prepare('UPDATE offers SET status = "cancelada", canceled_at = NOW(), updated_at = NOW() WHERE id = ?');
        $stmt->execute([$offerId]);
    }

    private function saveOfferVersion(int $offerId, int $adminId, string $title, string $description, string $finalMessage, string $feedback, string $source): void
    {
        $stmt = $this->db->prepare('SELECT COALESCE(MAX(version_number), 0) + 1 FROM offer_versions WHERE offer_id = ?');
        $stmt->execute([$offerId]);
        $version = (int) $stmt->fetchColumn();

        $stmt = $this->db->prepare(
            'INSERT INTO offer_versions (offer_id, version_number, title, description, final_text, feedback, source, admin_id, created_at)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, NOW())'
        );
        $stmt->execute([$offerId, $version, $title, $description, $finalMessage, $feedback, $source, $adminId]);
    }

    private function activeBuyersWithoutDuplicates(): array
    {
        $stmt = $this->db->query('SELECT * FROM buyers WHERE active = 1 ORDER BY name');
        $unique = [];
        foreach ($stmt->fetchAll() as $buyer) {
            $phone = normalize_phone((string) $buyer['phone']);
            if (!$phone || isset($unique[$phone])) {
                continue;
            }
            $buyer['normalized_phone'] = $phone;
            $unique[$phone] = $buyer;
        }
        return array_values($unique);
    }

    private function sendToBuyers(int $offerId, array $buyers, array $images, string $finalMessage): array
    {
        if (count($images) === 0) {
            app_log('warning', 'Offer has no image. MVP requires at least one image for sendMedia.', ['offer_id' => $offerId]);
            return ['total' => count($buyers), 'success' => 0, 'failures' => count($buyers), 'failure_details' => []];
        }

        $summary = ['total' => count($buyers), 'success' => 0, 'failures' => 0, 'failure_details' => []];
        foreach ($buyers as $buyer) {
            $buyerOk = true;
            $buyerErrors = [];
            foreach ($images as $index => $image) {
                $caption = $index === 0 ? $finalMessage : '';
                $result = $this->evolution->sendMedia(
                    (string) $buyer['normalized_phone'],
                    (string) $image['media'],
                    $caption,
                    (string) $image['mimetype']
                );
                $this->saveSendLog($offerId, (int) $buyer['id'], (string) $buyer['normalized_phone'], (int) $image['id'], $caption, $result);
                if (!$result['success']) {
                    $buyerOk = false;
                    $buyerErrors[] = (string) ($result['error'] ?? 'Erro desconhecido');
                }
            }

            if ($buyerOk) {
                $summary['success']++;
            } else {
                $summary['failures']++;
                $summary['failure_details'][] = [
                    'phone' => (string) $buyer['normalized_phone'],
                    'error' => implode(' | ', array_unique($buyerErrors)),
                ];
            }
        }
        return $summary;
    }

    private function saveSendLog(int $offerId, int $buyerId, string $phone, int $imageId, string $caption, array $result): void
    {
        $stmt = $this->db->prepare(
            'INSERT INTO send_logs
             (offer_id, buyer_id, buyer_phone, image_id, message_type, caption, success, evolution_message_id, error_message, created_at)
             VALUES (?, ?, ?, ?, "image", ?, ?, ?, ?, NOW())'
        );
        $stmt->execute([
            $offerId,
            $buyerId,
            $phone,
            $imageId,
            $caption,
            !empty($result['success']) ? 1 : 0,
            (string) ($result['message_id'] ?? ''),
            (string) ($result['error'] ?? ''),
        ]);
    }
}
