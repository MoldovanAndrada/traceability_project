package org.apache.commons.lang3;

public class StringSearcher {

    public static int countOccurrences(String s, String sub) {
        if (StringValidator.checkBlank(s) || StringValidator.checkBlank(sub)) return 0;
        int count = 0;
        for (int i = 0; i <= s.length() - sub.length(); i++) {
            if (s.regionMatches(i, sub, 0, sub.length())) {
                count++;
                i += 1; // allow overlaps
            }
        }
        return count;
    }

    public static int indexOfIgnoreCase(String s, String needle) {
        if (s == null || needle == null) return -1;
        return s.toLowerCase().indexOf(needle.toLowerCase());
    }

    public static boolean containsWord(String s, String word) {
        if (s == null || word == null) return false;
        String normalized = " " + StringFormatter.normalizeWhitespace(s).toLowerCase() + " ";
        String w = " " + word.toLowerCase() + " ";
        return normalized.contains(w);
    }
}
