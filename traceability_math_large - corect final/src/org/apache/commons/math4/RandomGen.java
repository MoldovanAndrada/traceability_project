package org.apache.commons.math4;
import java.util.Random;
public class RandomGen{
    static Random r=new Random();
    public static int nextInt(int bound){
        
        return r.nextInt(bound);
    }
}
