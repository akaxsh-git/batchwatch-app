package org.batchwatch.app

import android.app.Application
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import org.batchwatch.app.data.worker.AlertRecheckWorker
import java.util.concurrent.TimeUnit

class BatchWatchApp : Application() {

    override fun onCreate() {
        super.onCreate()
        setupPeriodicRecheck()
    }

    private fun setupPeriodicRecheck() {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

        val recheckRequest = PeriodicWorkRequestBuilder<AlertRecheckWorker>(24, TimeUnit.HOURS)
            .setConstraints(constraints)
            .build()

        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            "BatchWatchDailyRecheck",
            ExistingPeriodicWorkPolicy.KEEP,
            recheckRequest
        )
    }
}
