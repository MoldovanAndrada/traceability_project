package org.apache.commons.math4;
public class StatisticalService {
    public static double zScore(double[] values, double x) {
        double mean = StatsMean.mean(values);
        double var = StatsVariance.var(values);
        double std = RootFinder.sqrt(var);
        return (x - mean) / std;
    }
    public static double normalizedNorm(double[] values){
        double n = VectorNorm.norm(values);
        return Clamp.clamp((int)n, 0, 100);
    }
}
