package org.apache.commons.math4;
public class LinearAlgebraService {
    public static int[][] multiplyAndAdd(int[][] a, int[][] b, int[][] c) {
        int[][] mul = MatrixMul.mul(a, b);
        return MatrixAdd.add(mul, c);
    }

}
