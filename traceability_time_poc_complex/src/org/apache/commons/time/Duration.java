
package org.apache.commons.time;
public class Duration {
    private final long millis;
    public Duration(long millis) {
        if (millis < 0) throw new IllegalArgumentException("Negative duration");
        this.millis = millis;
    }
    public long toSeconds() {
        return millis / 1000;
    }
    public long toMinutes() {
        return millis / 60000;
    }
}
