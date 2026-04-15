package org.apache.commons.lang3;

import java.text.Normalizer;

public class StringFormatter {


    public static String toTitleCaseWords(String in) {
        if (in == null) return null;
        if (StringValidator.checkBlank(in)) return in;
        String[] parts = in.trim().split("\\s+");
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < parts.length; i++) {
            if (i > 0) sb.append(' ');
            sb.append(toFirstUpper(parts[i].toLowerCase()));
        }
        return sb.toString();
    }

    public static String removeAccents(String s) {
        if (s == null) return null;
        return Normalizer.normalize(s, Normalizer.Form.NFD).replaceAll("\\p{M}", "");
    }

    public static String normalizeWhitespace(String s) {
        if (s == null) return null;
        return s.trim().replaceAll("\\s+", " ");
    }

    public static String safeSubstring(String s, int start, int end) {
        if (s == null) return null;
        int a = Clamp.clamp(start, 0, s.length());
        int b = Clamp.clamp(end, 0, s.length());
        if (b < a) { int t = a; a = b; b = t; }
        return s.substring(a, b);
    }
}
