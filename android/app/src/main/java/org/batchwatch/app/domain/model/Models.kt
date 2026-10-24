package org.batchwatch.app.domain.model

enum class CheckVerdict(val label: String) {
    FLAGGED("FLAGGED"),
    POSSIBLE("POSSIBLE"),
    NOT_FOUND_IN_ALERTS("NOT FOUND IN PUBLISHED ALERTS")
}

data class MatchedAlert(
    val alertMonth: String,
    val listType: String,
    val sourceFile: String,
    val sno: Int,
    val page: Int,
    val product: String,
    val batch: String,
    val manufacturer: String,
    val nsqResult: String
) {
    fun citation(): String = "$sourceFile · S.No $sno · page $page"
}

data class CheckResult(
    val verdict: CheckVerdict,
    val queryBatch: String,
    val queryProduct: String?,
    val matchedAlerts: List<MatchedAlert>,
    val plainLanguageExplanation: String,
    val nextSteps: List<String>,
    val disclaimer: String,
    val isDemo: Boolean = false,
    val citation: String? = null
)

data class ScanDraft(
    val brand: String? = null,
    val manufacturer: String? = null,
    val batch: String = "",
    val expiry: String? = null,
    val confidence: Map<String, Float> = emptyMap(),
    val imageQualityWarning: String? = null,
    val photoUri: String? = null
)

data class Medicine(
    val id: Long = 0,
    val brand: String,
    val manufacturer: String,
    val batch: String,
    val expiry: String,
    val verdict: CheckVerdict,
    val citation: String? = null,
    val addedAt: Long = System.currentTimeMillis(),
    val lastCheckedAt: Long = System.currentTimeMillis()
)

enum class ExpiryAlertLevel {
    VALID,
    EXPIRING_SOON,
    EXPIRED,
    UNKNOWN
}
