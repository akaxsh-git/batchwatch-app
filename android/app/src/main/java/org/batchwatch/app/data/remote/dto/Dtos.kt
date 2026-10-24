package org.batchwatch.app.data.remote.dto

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass
import org.batchwatch.app.domain.model.CheckResult
import org.batchwatch.app.domain.model.CheckVerdict
import org.batchwatch.app.domain.model.MatchedAlert
import org.batchwatch.app.domain.model.ScanDraft

@JsonClass(generateAdapter = true)
data class ScanResponseDto(
    @Json(name = "brand") val brand: String?,
    @Json(name = "manufacturer") val manufacturer: String?,
    @Json(name = "batch") val batch: String?,
    @Json(name = "expiry") val expiry: String?,
    @Json(name = "confidence") val confidence: Map<String, Float>?,
    @Json(name = "image_quality_warning") val imageQualityWarning: String?
) {
    fun toDomain(photoUri: String?): ScanDraft = ScanDraft(
        brand = brand,
        manufacturer = manufacturer,
        batch = batch ?: "",
        expiry = expiry,
        confidence = confidence ?: emptyMap(),
        imageQualityWarning = imageQualityWarning,
        photoUri = photoUri
    )
}

@JsonClass(generateAdapter = true)
data class MatchedAlertDto(
    @Json(name = "alert_month") val alertMonth: String,
    @Json(name = "list_type") val listType: String,
    @Json(name = "source_file") val sourceFile: String,
    @Json(name = "sno") val sno: Int,
    @Json(name = "page") val page: Int,
    @Json(name = "product") val product: String,
    @Json(name = "batch") val batch: String,
    @Json(name = "manufacturer") val manufacturer: String,
    @Json(name = "nsq_result") val nsqResult: String
) {
    fun toDomain(): MatchedAlert = MatchedAlert(
        alertMonth = alertMonth,
        listType = listType,
        sourceFile = sourceFile,
        sno = sno,
        page = page,
        product = product,
        batch = batch,
        manufacturer = manufacturer,
        nsqResult = nsqResult
    )
}

@JsonClass(generateAdapter = true)
data class CheckRequestDto(
    @Json(name = "batch") val batch: String,
    @Json(name = "product") val product: String? = null,
    @Json(name = "manufacturer") val manufacturer: String? = null
)

@JsonClass(generateAdapter = true)
data class CheckResponseDto(
    @Json(name = "verdict") val verdict: String,
    @Json(name = "matched_alerts") val matchedAlerts: List<MatchedAlertDto>?,
    @Json(name = "plain_language_explanation") val plainLanguageExplanation: String,
    @Json(name = "next_steps") val nextSteps: List<String>?,
    @Json(name = "disclaimer") val disclaimer: String,
    @Json(name = "citation") val citation: String?
) {
    fun toDomain(queryBatch: String, queryProduct: String?): CheckResult {
        val checkVerdict = when (verdict.uppercase()) {
            "FLAGGED" -> CheckVerdict.FLAGGED
            "POSSIBLE" -> CheckVerdict.POSSIBLE
            else -> CheckVerdict.NOT_FOUND_IN_ALERTS
        }
        return CheckResult(
            verdict = checkVerdict,
            queryBatch = queryBatch,
            queryProduct = queryProduct,
            matchedAlerts = matchedAlerts?.map { it.toDomain() } ?: emptyList(),
            plainLanguageExplanation = plainLanguageExplanation,
            nextSteps = nextSteps ?: listOf(
                "Double-check the batch number stamped on the physical pack",
                "Consult your licensed pharmacist or doctor if you have concerns",
                "Keep this medicine in your digital cabinet to receive re-check alerts"
            ),
            disclaimer = disclaimer,
            isDemo = false,
            citation = citation
        )
    }
}

@JsonClass(generateAdapter = true)
data class RecheckItemRequestDto(
    @Json(name = "batch") val batch: String,
    @Json(name = "product") val product: String? = null
)

@JsonClass(generateAdapter = true)
data class RecheckResponseItemDto(
    @Json(name = "batch") val batch: String,
    @Json(name = "verdict") val verdict: String,
    @Json(name = "citation") val citation: String?,
    @Json(name = "plain_language_explanation") val plainLanguageExplanation: String?
)

@JsonClass(generateAdapter = true)
data class AlertVersionDto(
    @Json(name = "latest_alert_month") val latestAlertMonth: String,
    @Json(name = "version") val version: String
)
