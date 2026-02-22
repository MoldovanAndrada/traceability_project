package org.apache.commons.lang3;

public class ObjectUtils {

    public static <T> T defaultIfNull(T obj, T def) {
        return obj == null ? def : obj;
    }

    public static boolean equals(Object a, Object b) {
        return a == b || (a != null && a.equals(b));
    }

    public static <T> T requireNonNull(T obj, String message) {
        if (obj == null) throw new IllegalArgumentException(message);
        return obj;
    }

    public static boolean safeToStringContains(Object o, String token) {
        if (o == null || token == null) return false;
        return o.toString().contains(token);
    }
}
