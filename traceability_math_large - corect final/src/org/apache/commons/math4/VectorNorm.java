package org.apache.commons.math4;
public class VectorNorm{
    public static double norm(double[]v){
        double s=0;
        for(double d:v) s+=d*d;
        return Math.sqrt(s);
    }
}
