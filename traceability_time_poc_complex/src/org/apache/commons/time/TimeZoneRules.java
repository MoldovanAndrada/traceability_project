
package org.apache.commons.time;
public class TimeZoneRules {
    public static int offsetHours(String tz) {
        switch (tz) {
            case "UTC": return 0;
            case "CET": return 1;
            case "EST": return -5;
            default: throw new IllegalArgumentException("Unknown TZ");
        }
    }
}
