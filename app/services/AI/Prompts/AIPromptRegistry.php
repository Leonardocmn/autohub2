<?php

class AIPromptRegistry
{
    public static function systemFor(string $task): string
    {
        $base = 'Voce atua no AutoHub, um sistema de distribuicao de ofertas de veiculos. Responda em portugues do Brasil. Nunca exponha placa, vendedor, loja, telefone, endereco, localizacao, links ou qualquer dado de acesso direto ao veiculo.';

        if ($task === 'padronizar_descricao' || $task === 'corrigir_anuncio' || $task === 'analisar_oferta') {
            return $base . ' Retorne apenas JSON valido com title, description e final_message. O campo final_message deve conter a mensagem completa que sera enviada ao comprador, incluindo titulo, dados do veiculo, observacoes e chamada final.';
        }

        if ($task === 'remover_informacoes_sensiveis') {
            return $base . ' Remova dados sensiveis do texto e retorne apenas o texto limpo.';
        }

        if ($task === 'extrair_dados_veiculo') {
            return $base . ' Extraia dados do veiculo e retorne apenas JSON valido.';
        }

        return $base;
    }

    public static function padronizarDescricao(string $description): string
    {
        return "Descricao original:\n" . $description . "\n\nRetorne JSON neste formato:\n{\n  \"title\": \"NOVA OFERTA AUTOHUB\",\n  \"description\": \"Veiculo: ...\\nAno: ...\\nKM: ...\\nCambio: ...\\nCombustivel: ...\\nCor: ...\\nValor: ...\\nObservacoes: ...\",\n  \"final_message\": \"*NOVA OFERTA AUTOHUB*\\n\\nVeiculo: ...\\nAno: ...\\nKM: ...\\nCambio: ...\\nCombustivel: ...\\nCor: ...\\nValor: ...\\nObservacoes: ...\\n\\nInteressados, chamar a AutoHub.\"\n}\n\nRegras: remova vendedor, placa, telefone, loja, endereco, localizacao, links e qualquer dado de acesso direto. Nao inclua campos vazios inventados; use nao informado quando faltar.";
    }

    public static function corrigirDescricao(string $previousMessage, string $feedback): string
    {
        return "Anuncio anterior:\n" . $previousMessage . "\n\nFeedback do administrador:\n" . $feedback . "\n\nGere uma nova versao corrigida seguindo o mesmo JSON de padronizacao. Preserve a remocao de dados sensiveis.";
    }
}
