package org.apache.commons.math4;
public class StatsVariance{
    public static double var(double[] v){
        double m=StatsMean.mean(v);
        double s=0;
        for(double d:v) s+=(d-m)*(d-m);
        return s/v.length;
    }
}
