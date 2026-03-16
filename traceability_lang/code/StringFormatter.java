package org.apache.commons.lang3;

import java.text.Normalizer;

public class StringFormatter {

    public static String toFirstUpper(String in) {
        if (in == null) return null;
        if (in.isEmpty()) return in;
        return Character.toUpperCase(in.charAt(0)) + in.substring(1);
    }


    public static String removeAccents(String s) {
        if (s == null) return null;
        return Normalizer.normalize(s, Normalizer.Form.NFD).replaceAll("\\p{M}", "");
    }

    public static String normalizeWhitespace(String s) {
        if (s == null) return null;
        return s.trim().replaceAll("\\s+", " ");
    }


}
