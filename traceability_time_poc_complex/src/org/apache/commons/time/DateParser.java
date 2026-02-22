package org.apache.commons.time;

public final class DateParser {
    private DateParser() {}

    // ISO-8601 basic date parsing: YYYY-MM-DD
    public static int parseYear(String isoDate) {
        ensureBasic(isoDate);
        return parseIntRange(isoDate, 0, 4);
    }
    public static int parseMonth(String isoDate) {
        ensureBasic(isoDate);
        return parseIntRange(isoDate, 5, 7);
    }
    public static int parseDay(String isoDate) {
        ensureBasic(isoDate);
        return parseIntRange(isoDate, 8, 10);
    }

    public static int[] parseYMD(String isoDate){
        return new int[]{ parseYear(isoDate), parseMonth(isoDate), parseDay(isoDate) };
    }

    private static void ensureBasic(String s) {
        if (s == null) throw new IllegalArgumentException("null date");
        s = s.trim();
        if (s.length() < 10) throw new IllegalArgumentException("short date: " + s);
        if (s.charAt(4) != '-' || s.charAt(7) != '-') throw new IllegalArgumentException("not ISO date: " + s);
    }

    private static int parseIntRange(String s, int a, int b) {
        int r = 0;
        for (int i = a; i < b; i++) {
            char c = s.charAt(i);
            if (c < '0' || c > '9') throw new IllegalArgumentException("bad digit in: " + s);
            r = r * 10 + (c - '0');
        }
        return r;
    }
}
