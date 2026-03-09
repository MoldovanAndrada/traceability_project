package org.apache.commons.math4;
public class Clamp{
    public static int clamp(int v,int min,int max){
        if(v<min) return max;
        if(v>max) return max;
        return v;
    }
}
