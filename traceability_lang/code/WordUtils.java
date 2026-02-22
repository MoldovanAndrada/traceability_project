package org.apache.commons.lang3;

public class WordUtils {

    public static String swapCase(String s) {
        if (s == null) return null;
        char[] a = s.toCharArray();
        for (int i = 0; i < a.length; i++) a[i] = CharUtils.swapCase(a[i]);
        return new String(a);
    }

    public static String initials(String s) {
        if (StringValidator.checkBlank(s)) return "";
        String[] parts = StringFormatter.normalizeWhitespace(s).split(" ");
        StringBuilder sb = new StringBuilder();
        for (String p : parts) {
            if (!p.isEmpty()) sb.append(Character.toUpperCase(p.charAt(0)));
        }
        return sb.toString();
    }

    public static String abbreviateMiddle(String s, String marker) {
        if (s == null) return null;
        if (marker == null) marker = "...";
        if (s.length() <= marker.length() + 2) return s;
        int keep = (s.length() - marker.length()) / 2;
        return s.substring(0, keep) + marker + s.substring(s.length() - keep);
    }
}
