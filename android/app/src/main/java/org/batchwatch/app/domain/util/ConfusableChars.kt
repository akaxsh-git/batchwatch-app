package org.batchwatch.app.domain.util

object ConfusableChars {

    private val CONFUSABLE_MAP = mapOf(
        '0' to setOf('O', 'Q', 'D'),
        'O' to setOf('0', 'Q', 'D'),
        'Q' to setOf('0', 'O', 'D'),
        'D' to setOf('0', 'O'),

        '1' to setOf('I', 'L', '|'),
        'I' to setOf('1', 'L', '|'),
        'L' to setOf('1', 'I'),

        '2' to setOf('Z'),
        'Z' to setOf('2'),

        '5' to setOf('S'),
        'S' to setOf('5'),

        '6' to setOf('G'),
        'G' to setOf('6'),

        '8' to setOf('B'),
        'B' to setOf('8')
    )

    data class CharAnalysis(
        val index: Int,
        val char: Char,
        val isConfusable: Boolean,
        val possibleConfusion: List<Char>,
        val hint: String?
    )

    fun analyze(batch: String): List<CharAnalysis> {
        return batch.mapIndexed { idx, ch ->
            val upper = ch.uppercaseChar()
            val lookalikes = CONFUSABLE_MAP[upper]
            if (lookalikes != null) {
                val list = lookalikes.toList()
                val hint = "Easily misread as: ${list.joinToString(", ")}"
                CharAnalysis(
                    index = idx,
                    char = ch,
                    isConfusable = true,
                    possibleConfusion = list,
                    hint = hint
                )
            } else {
                CharAnalysis(
                    index = idx,
                    char = ch,
                    isConfusable = false,
                    possibleConfusion = emptyList(),
                    hint = null
                )
            }
        }
    }

    fun hasConfusables(batch: String): Boolean {
        return batch.any { CONFUSABLE_MAP.containsKey(it.uppercaseChar()) }
    }
}
