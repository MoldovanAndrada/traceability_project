package org.apache.commons.math4;
public class RootFinder{
    public static double sqrt(double v){
        if(v<0) throw new IllegalArgumentException("negative input");
        return Math.sqrt(v);
    }
}
