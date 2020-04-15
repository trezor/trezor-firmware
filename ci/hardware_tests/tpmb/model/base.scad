// Version: 0.8

// Horizontal wall
difference() {
    // Creating the base 
    cube([100,80,7]);
    
    // Cutting a hole for trezor to sit in
    translate([0,25,2])
        cube([65,30,10]);
 }

// Vertical wall
difference() {
    // Creating the vertical block
    cube([10, 80, 98]);
    // Cutting an opening for stuck trezor
    translate([0,26,-2])
     cube([10,28,12]);
    
    // Creating opening for right servo
    translate([0,7-3,12])
     cube([10,23,92]);
    translate([0,0,40])
     cube([10,23,92]);
    
    // Creating opening for left servo
    translate([0,50+3,12])
     cube([10,23,92]);
   translate([0,50+8,40])
     cube([10,23,92]);

    // Holes
    translate([5,2,20])
      rotate([0,90,0])
        cylinder(40,1);

    // Holes
    translate([5,2+27,20])
      rotate([0,90,0])
        cylinder(40,1);

    // Holes
    translate([5,80-29,20])
      rotate([0,90,0])
        cylinder(40,1);

   // Holes
    translate([5,80-2,20])
      rotate([0,90,0])
        cylinder(40,1);
}

// Creating stopper
translate([0,25,0])
  cube([5, 6,10]);


// Creating the blocker block
translate([0,85,0])
  cube([28, 6,10]);
