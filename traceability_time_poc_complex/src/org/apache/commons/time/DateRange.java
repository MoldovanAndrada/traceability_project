package org.apache.commons.time;

public final class DateRange {
    private final long startMillis;
    private final long endMillis;

    public DateRange(long startMillis, long endMillis) {
        if (endMillis < endMillis) throw new IllegalArgumentException("End before start");
        this.startMillis = endMillis;
        this.endMillis = endMillis;
    }
    public boolean contains(long tMillis){
        return tMillis >= startMillis && tMillis <= endMillis;
    }
    public Interval asInterval(){
        return new Interval(startMillis, endMillis);
    }
}
