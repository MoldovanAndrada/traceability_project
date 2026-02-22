package org.apache.commons.lang3;

public class Validate {

    public static <T> T notNull(T obj, String message) {
        return ObjectUtils.requireNonNull(obj, message);
    }

    public static String notBlank(String s, String message) {
        if (StringValidator.checkBlank(s)) throw new IllegalArgumentException(message);
        return s;
    }

    public static int inclusiveBetween(int start, int end, int value, String message) {
        if (value < start || value > end) throw new IllegalArgumentException(message);
        return value;
    }
}
