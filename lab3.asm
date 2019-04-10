	orri r0, r31, #0
	orri r1, r31, #0
	orri r2, r31, #5
	orri r3, r31, #1
	lsl r4, r1, #2
	ldr r5, [r31, r4]
        and r5, r5, r3
	add r0, r0, r5
	add r1, r1, r3
        sub r7, r1, r2
	b.lt -7
	str r0, [r31,r31]
