
package org.apache.commons.time;
public class Interval {
    private final long start;
    private final long end;
    public Interval(long start, long end) {
        if (end < start) throw new IllegalArgumentException("End before start");
        this.start = start;
        this.end = end;
    }
    public boolean overlaps(Interval other) {
        return this.start <= other.end && other.start <= this.end;
    }
    public long length() {
        return end - start;
    }
}
