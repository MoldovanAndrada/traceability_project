package org.apache.commons.math4;
public class LogUtils{
    public static double log(double v){
        if(v<=0) throw new IllegalArgumentException("non-positive input");
        return Math.log(v);
    }
}
