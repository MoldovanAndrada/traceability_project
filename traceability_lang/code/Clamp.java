package org.apache.commons.lang3;

public class Clamp {
    public static int clamp(int v, int min, int max){
        if (min > max) { int t=min; min=max; max=t; }
        if (v < min) return min;
        if (v > max) return max;
        return v;
    }
}
