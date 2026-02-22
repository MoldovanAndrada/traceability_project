package org.apache.commons.lang3;

import java.util.regex.Pattern;

public class RegExUtils {

    public static String replaceAll(String input, String regex, String replacement) {
        Validate.notNull(regex, "regex");
        if (input == null) return null;
        return Pattern.compile(regex).matcher(input).replaceAll(ObjectUtils.defaultIfNull(replacement, ""));
    }

    public static String safeReplaceLiteral(String input, String literal, String replacement) {
        Validate.notNull(literal, "literal");
        if (input == null) return null;
        String safe = Pattern.quote(literal);
        return replaceAll(input, safe, ObjectUtils.defaultIfNull(replacement, ""));
    }

    public static boolean matchesSafe(String input, String regex) {
        if (input == null || regex == null) return false;
        return Pattern.compile(regex).matcher(StringFormatter.normalizeWhitespace(input)).find();
    }
}
