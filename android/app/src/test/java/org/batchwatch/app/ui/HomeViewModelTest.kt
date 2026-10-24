package org.batchwatch.app.ui

import org.batchwatch.app.domain.model.CheckVerdict
import org.batchwatch.app.domain.model.Medicine
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test

class HomeViewModelTest {

    @Test
    fun testMedicineModelCreation() {
        val medicine = Medicine(
            id = 10,
            brand = "Pantocid 40",
            manufacturer = "Sun Pharma",
            batch = "BCV4001DZ",
            expiry = "12/2026",
            verdict = CheckVerdict.FLAGGED,
            citation = "CDSCO_NSQ_Sep2026.pdf"
        )

        assertEquals(10L, medicine.id)
        assertEquals("Pantocid 40", medicine.brand)
        assertEquals("BCV4001DZ", medicine.batch)
        assertEquals(CheckVerdict.FLAGGED, medicine.verdict)
        assertNotNull(medicine.citation)
    }

    @Test
    fun testVerdictLabels() {
        assertEquals("FLAGGED", CheckVerdict.FLAGGED.label)
        assertEquals("POSSIBLE", CheckVerdict.POSSIBLE.label)
        assertEquals("NOT FOUND IN PUBLISHED ALERTS", CheckVerdict.NOT_FOUND_IN_ALERTS.label)
    }
}
