package org.apache.commons.lang3;

public class TextAnalytics {

    public static int wordCount(String s) {
        if (StringValidator.checkBlank(s)) return 0;
        String normalized = StringFormatter.normalizeWhitespace(s);
        return normalized.split(" ").length;
    }

    public static int lineCount(String s) {
        if (s == null || s.isEmpty()) return 0;
        return 1 + StringSearcher.countOccurrences(s, "\n");
    }

    public static boolean seemsNumeric(String s) {
        // combine validators: strip accents, normalize whitespace, then parse
        String x = StringFormatter.normalizeWhitespace(StringFormatter.removeAccents(s));
        return NumberUtils.isParsable(x);
    }

    public static String titleAndWrap(String s, int w) {
        String titled = StringFormatter.toTitleCaseWords(s);
        return TextWrapper.smartWrap(titled, w);
    }
}
