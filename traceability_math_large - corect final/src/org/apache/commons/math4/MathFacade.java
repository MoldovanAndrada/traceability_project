package org.apache.commons.math4;
public class MathFacade {
    public static double computeStatistics(double[] values) {
        return StatisticalService.zScore(values, values[0]);
    }
    public static int[][] processMatrices(int[][] a, int[][] b, int[][] c) {
        return LinearAlgebraService.multiplyAndAdd(a, b, c);
    }
    public static int numberAnalysis(int a, int b) {
        return NumberTheoryService.fibGcd(a, b);
    }
    public static double advanced(int a, int b, double x) {
        return AdvancedMathService.computeExpression(a, b, x);
    }
}
