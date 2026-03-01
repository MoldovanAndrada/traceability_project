package org.apache.commons.time;

public final class DateRange {
    private final long startMillis;
    private final long endMillis;

    public DateRange(long startMillis, long endMillis) {
        if (endMillis < startMillis) throw new IllegalArgumentException("End before start");
        this.startMillis = startMillis;
        this.endMillis = endMillis;
    }
    public boolean contains(long tMillis){
        return tMillis >= startMillis && tMillis <= endMillis;
    }
    public Interval asInterval(){
        return new Interval(startMillis, endMillis);
    }
}
