package org.batchwatch.app.data.repository

import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import org.batchwatch.app.data.local.MedicineDao
import org.batchwatch.app.data.local.MedicineEntity
import org.batchwatch.app.data.local.UserPreferences
import org.batchwatch.app.domain.model.CheckResult
import org.batchwatch.app.domain.model.CheckVerdict
import org.batchwatch.app.domain.model.MatchedAlert
import org.batchwatch.app.domain.model.Medicine
import org.batchwatch.app.domain.model.ScanDraft
import java.util.Locale

class DemoRepository(
    private val medicineDao: MedicineDao,
    private val preferences: UserPreferences
) : MedicineRepository {

    override val isDemoMode: Boolean = true

    // Internal demo flag that can be toggled by Settings / simulate button
    private var simulatedNewAlertActive: Boolean = false

    override suspend fun scanImage(imageBytes: ByteArray, photoUri: String?): Result<ScanDraft> {
        // Return Pantoprazole scan scenario:
        // Batch read as "BCV4OO1DZ" with 62% confidence
        val draft = ScanDraft(
            brand = "Pantocid 40",
            manufacturer = "Sun Pharma Laboratories",
            batch = "BCV4OO1DZ",
            expiry = "12/2026",
            confidence = mapOf(
                "batch_number" to 0.62f,
                "brand_name" to 0.94f,
                "manufacturer" to 0.88f,
                "expiry_date" to 0.91f
            ),
            imageQualityWarning = null,
            photoUri = photoUri
        )
        return Result.success(draft)
    }

    override suspend fun checkBatch(
        batch: String,
        product: String?,
        manufacturer: String?
    ): Result<CheckResult> {
        val cleanBatch = batch.trim().uppercase(Locale.ROOT)
        val cleanProd = (product ?: "").trim().uppercase(Locale.ROOT)

        val result = when {
            // Scenario 1: Cefixime -> FLAGGED in 2 alerts
            cleanBatch == "CFX2024" || cleanProd.contains("CEFIXIME") -> {
                val alerts = listOf(
                    MatchedAlert(
                        alertMonth = "August 2026",
                        listType = "NSQ",
                        sourceFile = "CDSCO_NSQ_Aug2026.pdf",
                        sno = 14,
                        page = 2,
                        product = "Cefixime Tablets IP 200mg",
                        batch = "CFX2024",
                        manufacturer = "BioPharma Formulations Pvt Ltd",
                        nsqResult = "Failed dissolution test and assay of active ingredient"
                    ),
                    MatchedAlert(
                        alertMonth = "July 2026",
                        listType = "NSQ",
                        sourceFile = "CDSCO_NSQ_Jul2026.pdf",
                        sno = 38,
                        page = 4,
                        product = "Cefixime Tablets IP 200mg",
                        batch = "CFX2024",
                        manufacturer = "BioPharma Formulations Pvt Ltd",
                        nsqResult = "Failed dissolution test"
                    )
                )
                CheckResult(
                    verdict = CheckVerdict.FLAGGED,
                    queryBatch = batch,
                    queryProduct = product ?: "Cefixime Tablets",
                    matchedAlerts = alerts,
                    plainLanguageExplanation = "Government drug testing laboratories flagged this batch because laboratory tests showed the medicine does not dissolve properly in the body, meaning patients may not absorb the required therapeutic dose. Found in 2 separate CDSCO alerts.",
                    nextSteps = listOf(
                        "Check the physical strip to verify the batch code CFX2024",
                        "Contact your prescribing doctor or dispensing pharmacist to confirm",
                        "Do not discard the strip if you intend to report it to the State Drug Control office"
                    ),
                    disclaimer = "General regulatory information only. Not medical advice.",
                    isDemo = true,
                    citation = "CDSCO_NSQ_Aug2026.pdf · S.No 14 · page 2 (Demo data)"
                )
            }

            // Scenario 2: Pantoprazole misread BCV4OO1DZ -> POSSIBLE
            cleanBatch == "BCV4OO1DZ" -> {
                val candidateAlert = MatchedAlert(
                    alertMonth = "September 2026",
                    listType = "NSQ",
                    sourceFile = "CDSCO_NSQ_Sep2026.pdf",
                    sno = 22,
                    page = 3,
                    product = "Pantoprazole Gastro-resistant Tablets IP",
                    batch = "BCV4001DZ",
                    manufacturer = "Sun Pharma Laboratories",
                    nsqResult = "Failed description and identification test"
                )
                CheckResult(
                    verdict = CheckVerdict.POSSIBLE,
                    queryBatch = batch,
                    queryProduct = product ?: "Pantocid 40",
                    matchedAlerts = listOf(candidateAlert),
                    plainLanguageExplanation = "Your batch 'BCV4OO1DZ' closely resembles listed alert batch 'BCV4001DZ'. The letters 'OO' are commonly confused with the digits '00' in camera optical scanning. Please verify whether the pack shows zeros.",
                    nextSteps = listOf(
                        "Inspect your physical blister pack under good light",
                        "If the batch has zeros (BCV4001DZ), re-run the check with the corrected digits",
                        "Speak to your pharmacist if the print on the foil is faint or rubbed off"
                    ),
                    disclaimer = "General regulatory information only. Not medical advice.",
                    isDemo = true,
                    citation = "CDSCO_NSQ_Sep2026.pdf · S.No 22 · page 3 (Demo data)"
                )
            }

            // Scenario 2 (Corrected): BCV4001DZ -> FLAGGED
            cleanBatch == "BCV4001DZ" -> {
                val alert = MatchedAlert(
                    alertMonth = "September 2026",
                    listType = "NSQ",
                    sourceFile = "CDSCO_NSQ_Sep2026.pdf",
                    sno = 22,
                    page = 3,
                    product = "Pantoprazole Gastro-resistant Tablets IP",
                    batch = "BCV4001DZ",
                    manufacturer = "Sun Pharma Laboratories",
                    nsqResult = "Failed description and identification test"
                )
                CheckResult(
                    verdict = CheckVerdict.FLAGGED,
                    queryBatch = batch,
                    queryProduct = product ?: "Pantoprazole Tablets",
                    matchedAlerts = listOf(alert),
                    plainLanguageExplanation = "This batch was flagged in the September 2026 CDSCO drug quality alert due to failed laboratory identification tests.",
                    nextSteps = listOf(
                        "Check the pack to confirm the batch is BCV4001DZ",
                        "Show this alert record to your dispensing pharmacist",
                        "Keep the invoice and pack if reporting to drug control authorities"
                    ),
                    disclaimer = "General regulatory information only. Not medical advice.",
                    isDemo = true,
                    citation = "CDSCO_NSQ_Sep2026.pdf · S.No 22 · page 3 (Demo data)"
                )
            }

            // Scenario 3: Telmisartan -> NOT FOUND IN PUBLISHED ALERTS (unless simulated)
            cleanBatch == "TEL2026B" || cleanProd.contains("TELMISARTAN") -> {
                if (simulatedNewAlertActive) {
                    val alert = MatchedAlert(
                        alertMonth = "October 2026",
                        listType = "NSQ",
                        sourceFile = "CDSCO_NSQ_Oct2026.pdf",
                        sno = 5,
                        page = 1,
                        product = "Telmisartan Tablets IP 40mg",
                        batch = "TEL2026B",
                        manufacturer = "Apex LifeSciences Pvt Ltd",
                        nsqResult = "Assay of Telmisartan 78.4% (standard limits 90.0% to 110.0%)"
                    )
                    CheckResult(
                        verdict = CheckVerdict.FLAGGED,
                        queryBatch = batch,
                        queryProduct = product ?: "Telmisartan 40",
                        matchedAlerts = listOf(alert),
                        plainLanguageExplanation = "Flagged in the newly published October 2026 CDSCO alert: laboratory assay found active ingredient below the mandated pharmacopoeial range.",
                        nextSteps = listOf(
                            "Check the blister strip details",
                            "Consult your healthcare provider or pharmacist for guidance",
                            "Save to your cabinet for ongoing status monitoring"
                        ),
                        disclaimer = "General regulatory information only. Not medical advice.",
                        isDemo = true,
                        citation = "CDSCO_NSQ_Oct2026.pdf · S.No 5 · page 1 (Demo data)"
                    )
                } else {
                    CheckResult(
                        verdict = CheckVerdict.NOT_FOUND_IN_ALERTS,
                        queryBatch = batch,
                        queryProduct = product ?: "Telmisartan 40",
                        matchedAlerts = emptyList(),
                        plainLanguageExplanation = "This batch number was not found in any published CDSCO alert lists. This indicates no state drug testing laboratory has flagged this batch.",
                        nextSteps = listOf(
                            "Ensure the packaging and tamper-evident seal are intact",
                            "Check the expiration date printed on the foil strip",
                            "Save this medicine to your cabinet so BatchWatch can alert you if new reports are published"
                        ),
                        disclaimer = "General regulatory information only. 'Not found in published alerts' does not certify clinical efficacy or authenticity.",
                        isDemo = true,
                        citation = null
                    )
                }
            }

            // Default fallback for any manual search in demo mode
            else -> {
                CheckResult(
                    verdict = CheckVerdict.NOT_FOUND_IN_ALERTS,
                    queryBatch = batch,
                    queryProduct = product,
                    matchedAlerts = emptyList(),
                    plainLanguageExplanation = "No matching records found for batch '$batch' in our published alert database.",
                    nextSteps = listOf(
                        "Verify that all letters and digits match your pack exactly",
                        "Save to your medicine cabinet for automated future re-checks"
                    ),
                    disclaimer = "General regulatory information only. Not found in published alerts does not certify safety.",
                    isDemo = true,
                    citation = null
                )
            }
        }

        return Result.success(result)
    }

    override suspend fun recheckAll(): Result<List<Pair<Medicine, CheckResult>>> {
        val allEntities = medicineDao.getAllMedicines()
        // Simple flow emission snapshot
        val results = mutableListOf<Pair<Medicine, CheckResult>>()
        return Result.success(results)
    }

    override fun getSavedMedicines(): Flow<List<Medicine>> {
        return medicineDao.getAllMedicines().map { list ->
            list.map { it.toDomain() }
        }
    }

    override suspend fun saveMedicine(medicine: Medicine): Long {
        return medicineDao.insertMedicine(MedicineEntity.fromDomain(medicine))
    }

    override suspend fun deleteMedicine(id: Long) {
        medicineDao.deleteById(id)
    }

    override suspend fun getMedicineById(id: Long): Medicine? {
        return medicineDao.getMedicineById(id)?.toDomain()
    }

    override suspend fun simulateNewAlertForTelmisartan(): Boolean {
        simulatedNewAlertActive = !simulatedNewAlertActive
        preferences.setSimulateNewAlert(simulatedNewAlertActive)

        // If active, update any saved Telmisartan in Room to FLAGGED to trigger UI/notification test
        val existing = medicineDao.getMedicineByBatch("TEL2026B")
        if (existing != null) {
            val updated = existing.copy(
                verdict = if (simulatedNewAlertActive) CheckVerdict.FLAGGED.name else CheckVerdict.NOT_FOUND_IN_ALERTS.name,
                citation = if (simulatedNewAlertActive) "CDSCO_NSQ_Oct2026.pdf · S.No 5 (Demo)" else null,
                lastCheckedAt = System.currentTimeMillis()
            )
            medicineDao.updateMedicine(updated)
        }
        return simulatedNewAlertActive
    }
}
