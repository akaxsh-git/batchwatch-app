package org.batchwatch.app.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey
import org.batchwatch.app.domain.model.CheckVerdict
import org.batchwatch.app.domain.model.Medicine

@Entity(tableName = "saved_medicines")
data class MedicineEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val brand: String,
    val manufacturer: String,
    val batch: String,
    val expiry: String,
    val verdict: String,
    val citation: String?,
    val addedAt: Long = System.currentTimeMillis(),
    val lastCheckedAt: Long = System.currentTimeMillis()
) {
    fun toDomain(): Medicine = Medicine(
        id = id,
        brand = brand,
        manufacturer = manufacturer,
        batch = batch,
        expiry = expiry,
        verdict = try { CheckVerdict.valueOf(verdict) } catch (_: Exception) { CheckVerdict.NOT_FOUND_IN_ALERTS },
        citation = citation,
        addedAt = addedAt,
        lastCheckedAt = lastCheckedAt
    )

    companion object {
        fun fromDomain(m: Medicine): MedicineEntity = MedicineEntity(
            id = m.id,
            brand = m.brand,
            manufacturer = m.manufacturer,
            batch = m.batch,
            expiry = m.expiry,
            verdict = m.verdict.name,
            citation = m.citation,
            addedAt = m.addedAt,
            lastCheckedAt = m.lastCheckedAt
        )
    }
}
