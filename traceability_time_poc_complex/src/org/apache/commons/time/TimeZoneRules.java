package org.apache.commons.time;

public final class TimeZoneRules {
    private TimeZoneRules() {}
    public static int offsetMinutes(String tz) {
        if (tz == null) throw new IllegalArgumentException("null tz");
        switch (tz) {
            case "UTC": return 0;
            case "CET": return 60;
            case "EET": return 120;
            case "EST": return -300;
            case "PST": return -480;
            default: throw new IllegalArgumentException("Unknown TZ: " + tz);
        }
    }
}
