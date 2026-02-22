package org.apache.commons.lang3;

public class NumberUtils {

    public static boolean isParsable(String s) {
        if (StringValidator.checkBlank(s)) return false;
        try {
            Double.parseDouble(s.trim());
            return true;
        } catch (RuntimeException ex) {
            return false;
        }
    }

    public static int parseIntOrDefault(String s, int def) {
        if (!isParsable(s)) return def;
        try {
            return Integer.parseInt(s.trim());
        } catch (RuntimeException ex) {
            return def;
        }
    }

    public static int clampInt(int v, int min, int max) {
        return Clamp.clamp(v, min, max);
    }

    public static void requireInRange(int v, int min, int max, String message) {
        if (v < min || v > max) throw new IllegalArgumentException(message);
    }
}
