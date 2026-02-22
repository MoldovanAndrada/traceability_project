package org.apache.commons.lang3;

public class StringValidator {

    public static boolean checkBlank(CharSequence cs) {
        if (cs == null) return true;
        for (int i = 0; i < cs.length(); i++) {
            if (!CharUtils.isWhitespace(cs.charAt(i))) return false;
        }
        return true;
    }

    public static boolean isAsciiPrintable(String s) {
        if (s == null) return false;
        for (int i = 0; i < s.length(); i++) {
            if (!CharUtils.isAsciiPrintable(s.charAt(i))) return false;
        }
        return true;
    }

    public static boolean isPalindrome(String s) {
        if (s == null) return false;
        String cleaned = StringFormatter.normalizeWhitespace(StringFormatter.removeAccents(s)).replace(" ", "").toLowerCase();
        if (cleaned.isEmpty()) return true;
        return cleaned.equals(StringUtils.reverse(cleaned));
    }

    public static void requireNotBlank(String s, String message) {
        if (checkBlank(s)) throw new IllegalArgumentException(message);
    }
}
