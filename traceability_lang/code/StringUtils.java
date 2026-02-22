package org.apache.commons.lang3;

public class StringUtils {

    public static String capitalize(String s) { return StringFormatter.toFirstUpper(s); }

    public static String titleCase(String s) { return StringFormatter.toTitleCaseWords(s); }

    public static boolean isBlank(CharSequence cs) { return StringValidator.checkBlank(cs); }

    public static String reverse(String s) {
        if (s == null) return null;
        char[] a = s.toCharArray();
        ArrayUtils.reverseArray(a);
        return new String(a);
    }

    public static String wrap(String s, int w) { return TextWrapper.wrap(s, w); }

    public static String smartWrap(String s, int w) { return TextWrapper.smartWrap(s, w); }

    public static boolean isNumeric(String s) { return NumberUtils.isParsable(s); }

    public static String stripAccents(String s) { return StringFormatter.removeAccents(s); }

    public static boolean isPalindrome(String s) { return StringValidator.isPalindrome(s); }

    public static int countMatches(String s, String sub) { return StringSearcher.countOccurrences(s, sub); }

    public static String normalizeAndCapitalize(String s) { return LangFacade.normalizeAndCapitalize(s); }
}
