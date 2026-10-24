package org.batchwatch.app.domain

import org.batchwatch.app.domain.util.ConfusableChars
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ConfusableCharsTest {

    @Test
    fun testDetectsZeroAndO() {
        val analysis = ConfusableChars.analyze("BCV4001DZ")
        assertTrue(analysis.any { it.char == '0' && it.isConfusable })
        assertTrue(analysis.any { it.char == 'D' && it.isConfusable })
        assertTrue(analysis.any { it.char == 'Z' && it.isConfusable })
    }

    @Test
    fun testDetectsOneAndI() {
        val analysis = ConfusableChars.analyze("MED123I")
        assertTrue(analysis.any { it.char == '1' && it.isConfusable })
        assertTrue(analysis.any { it.char == 'I' && it.isConfusable })
    }

    @Test
    fun testDetectsFiveAndS() {
        val analysis = ConfusableChars.analyze("S5")
        assertTrue(analysis.any { it.char == 'S' && it.isConfusable })
        assertTrue(analysis.any { it.char == '5' && it.isConfusable })
    }

    @Test
    fun testDetectsEightAndB() {
        val analysis = ConfusableChars.analyze("B8")
        assertTrue(analysis.any { it.char == 'B' && it.isConfusable })
        assertTrue(analysis.any { it.char == '8' && it.isConfusable })
    }

    @Test
    fun testNonConfusableChars() {
        val analysis = ConfusableChars.analyze("MNTX")
        assertTrue(analysis.none { it.isConfusable })
    }

    @Test
    fun testHasConfusablesHelper() {
        assertTrue(ConfusableChars.hasConfusables("BCV4OO1DZ"))
        assertFalse(ConfusableChars.hasConfusables("MNPK"))
    }
}
