fn sum(n:int) -> int {
  let s:int = 0;        
  while (n > 0) {
    s = s + n;
    n = n - 1;
  }
  return s;
}

fn main() -> int {
  println(sum(10));
  return 0;
}
