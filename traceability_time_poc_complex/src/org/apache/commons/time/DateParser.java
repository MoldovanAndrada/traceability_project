
package org.apache.commons.time;
public class DateParser {
    public static int parseYear(String iso) {
        if (iso == null || iso.length() < 4) throw new IllegalArgumentException();
        return Integer.parseInt(iso.substring(0,4));
    }
    public static int parseMonth(String iso) {
        return Integer.parseInt(iso.substring(5,7));
    }
}
