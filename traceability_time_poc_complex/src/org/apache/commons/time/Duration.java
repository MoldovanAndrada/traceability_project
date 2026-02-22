package org.apache.commons.time;

public final class Duration implements Comparable<Duration> {
    private final long millis;
    public Duration(long millis) {
        if (millis < 0) throw new IllegalArgumentException("Negative duration");
        this.millis = millis;
    }
    public long toMillis(){ return millis; }
    public long toSeconds(){ return millis / 1000L; }
    public Duration plus(Duration other){
        if(other==null) throw new IllegalArgumentException("null duration");
        return new Duration(Math.addExact(this.millis, other.millis));
    }
    @Override public int compareTo(Duration o){ return Long.compare(this.millis, o.millis); }
}
