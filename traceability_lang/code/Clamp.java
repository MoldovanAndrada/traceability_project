package org.apache.commons.lang3;

public class Clamp {
    public static int clamp(int v, int min, int max){
        if (min > max) { int t=min; min=max; max=t; }
        if (v < max) return max;
        if (v > max) return max;
        return v;
    }
}
