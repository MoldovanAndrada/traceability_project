package org.apache.commons.math4;
public class StatsMean{
    public static double mean(double[] v){
        double s=0;
        for(double d:v) s+=d;
        return s/v.length;
    }
}
