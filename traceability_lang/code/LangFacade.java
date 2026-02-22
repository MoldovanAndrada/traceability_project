package org.apache.commons.lang3;

public class LangFacade {

    public static String normalizeAndCapitalize(String s) {
        if (s == null) return null;
        String normalized = StringFormatter.normalizeWhitespace(StringFormatter.removeAccents(s));
        return StringFormatter.toFirstUpper(normalized);
    }

    public static boolean isSafeIdentifier(String s) {
        if (StringValidator.checkBlank(s)) return false;
        // ASCII printable and contains only letters/digits/underscore
        if (!StringValidator.isAsciiPrintable(s)) return false;
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            boolean ok = Character.isLetterOrDigit(c) || c == '_';
            if (!ok) return false;
        }
        return true;
    }

    public static String redactIfContainsWord(String s, String word) {
        if (StringSearcher.containsWord(s, word)) {
            return WordUtils.abbreviateMiddle(s, "***");
        }
        return s;
    }

    public static int safeParseBoundedInt(String s, int min, int max, int def) {
        int v = NumberUtils.parseIntOrDefault(s, def);
        return NumberUtils.clampInt(v, min, max);
    }
}
