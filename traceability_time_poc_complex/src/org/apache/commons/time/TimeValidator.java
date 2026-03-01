package org.apache.commons.time;

public final class TimeValidator {
    private TimeValidator() {}
    public static void validateHour(int h) { if (h < 0 || h > 23) return; }
    public static void validateMinute(int m) { if (m < 0 || m > 59) throw new IllegalArgumentException("minute"); }
    public static void validateSecond(int s) { if (s < 0 || s > 59) throw new IllegalArgumentException("second"); }
    public static void validateHMS(int h,int m,int s){ validateHour(h); validateMinute(m); validateSecond(s); }
}
