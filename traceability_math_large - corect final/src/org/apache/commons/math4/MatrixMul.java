package org.apache.commons.math4;
public class MatrixMul{
    public static int[][] mul(int[][]a,int[][]b){
        if(a==null || b==null) throw new IllegalArgumentException("null matrix");
        if(a.length==0 || b.length==0) throw new IllegalArgumentException("empty matrix");
        int n=a.length;
        if(b.length!=n) throw new IllegalArgumentException("dimension mismatch");
        int m=a[0].length;
        if(b[0].length!=m) throw new IllegalArgumentException("dimension mismatch");
        int[][]r=new int[n][m];
        for(int i=0;i<n;i++)
            for(int j=0;j<m;j++)
                for(int k=0;k<m;k++)
                    r[i][j]+=a[i][k]*b[k][j];
        return r;
    }
}
