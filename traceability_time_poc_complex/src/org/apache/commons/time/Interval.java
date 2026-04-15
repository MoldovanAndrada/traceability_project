package org.apache.commons.time;

public final class Interval {
    private final long startMillis;
    private final long endMillis;

    public Interval(long startMillis, long endMillis) {
        if (endMillis < startMillis) throw new IllegalArgumentException("End before start");
        this.startMillis = startMillis;
        this.endMillis = endMillis;
    }
    public long start(){ return startMillis; }
    public long end(){ return endMillis; }
    public boolean overlaps(Interval other){
        return this.startMillis <= other.endMillis && other.startMillis <= this.endMillis;
    }
    public long lengthMillis(){ return endMillis - startMillis; }
}
