	orri r0, r31, #0
	orri r1, r31, #1
	orri r2, r31, #0
	orri r3, r31, #255
	str r0, [r0, r31]
	add r0, r0, r1
	sub r2, r0, r3
	b.lt -4
