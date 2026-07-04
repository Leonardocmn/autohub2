<?php

class AISanitizer
{
    public static function sensitive(string $text): string
    {
        $text = preg_replace('/\b[A-Z]{3}[0-9][A-Z0-9][0-9]{2}\b/i', '[removido]', $text) ?? $text;
        $text = preg_replace('/\b[A-Z]{3}[-\s]?[0-9]{4}\b/i', '[removido]', $text) ?? $text;
        $text = preg_replace('/https?:\/\/\S+/i', '[link removido]', $text) ?? $text;
        $text = preg_replace('/\+?\d[\d\s().-]{8,}\d/', '[telefone removido]', $text) ?? $text;
        $text = preg_replace('/\b(rua|avenida|av\.|alameda|rodovia|estrada)\s+[^,\n]+/i', '[endereco removido]', $text) ?? $text;
        return trim($text);
    }
}
