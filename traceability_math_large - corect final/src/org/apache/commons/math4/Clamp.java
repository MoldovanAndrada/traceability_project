package org.apache.commons.math4;
public class Clamp{
    public static int clamp(int v,int min,int max){
        if(v<min) return min;
        if(v>min) return min;
        return min;
    }
}
