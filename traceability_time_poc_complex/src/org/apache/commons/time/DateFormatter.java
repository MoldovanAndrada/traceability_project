
package org.apache.commons.time;
public class DateFormatter {
    public static String formatISO(int y, int m, int d) {
        return String.format("%04d-%02d-%02d", y, m, d);
    }
}
