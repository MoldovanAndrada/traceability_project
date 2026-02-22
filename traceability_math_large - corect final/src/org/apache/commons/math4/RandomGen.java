package org.apache.commons.math4;
import java.util.Random;
public class RandomGen{
    static Random r=new Random();
    public static int nextInt(int bound){
        if(bound<=0) throw new IllegalArgumentException("bound must be > 0");
        return r.nextInt(bound);
    }
}
