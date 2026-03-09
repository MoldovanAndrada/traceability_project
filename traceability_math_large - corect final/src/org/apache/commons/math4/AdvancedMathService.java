package org.apache.commons.math4;
public class AdvancedMathService {
    public static double computeExpression(int a, int b, double x) {
        int sum = ArithmeticUtils.add(a, b);
        double ratio = ArithmeticUtils.div(sum, x);
        return LogUtils.log(ratio);
    }
    public static double angleBasedComputation(double degrees) {
        double radians = AngleUtils.toRadians(degrees);
        return RootFinder.sqrt(radians);
    }
}
