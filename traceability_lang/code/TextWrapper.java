package org.apache.commons.lang3;

public class TextWrapper {

    public static String wrap(String str, int w) {
        if (str == null) return null;
        if (w < 1) return str;
        String s = StringFormatter.normalizeWhitespace(str);
        return s.length() > w ? s.substring(0, w) + "\n" + s.substring(w) : s;
    }

    public static String smartWrap(String str, int w) {
        if (str == null) return null;
        if (w < 1) return str;
        String s = StringFormatter.normalizeWhitespace(str);
        if (s.length() <= w) return s;

        int breakAt = s.lastIndexOf(' ', w);
        if (breakAt <= 0) breakAt = w;
        String left = s.substring(0, breakAt).trim();
        String right = s.substring(breakAt).trim();

        // avoid producing empty lines
        if (StringValidator.checkBlank(left)) return s;
        return left + "\n" + right;
    }

    public static int visualWidth(String s, int tabWidth) {
        if (s == null) return 0;
        int w = 0;
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '\t') w += tabWidth;
            else w += 1;
        }
        return w;
    }
}
