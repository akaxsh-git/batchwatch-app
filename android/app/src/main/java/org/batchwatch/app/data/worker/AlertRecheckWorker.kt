package org.batchwatch.app.data.worker

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import kotlinx.coroutines.flow.first
import org.batchwatch.app.BuildConfig
import org.batchwatch.app.MainActivity
import org.batchwatch.app.R
import org.batchwatch.app.data.local.AppDatabase
import org.batchwatch.app.data.local.UserPreferences
import org.batchwatch.app.data.repository.RepositoryProvider
import org.batchwatch.app.domain.model.CheckVerdict

class AlertRecheckWorker(
    private val context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {

    companion object {
        const val CHANNEL_ID = "batchwatch_alerts_channel"
        const val NOTIFICATION_ID_BASE = 5000
    }

    override suspend fun doWork(): Result {
        return try {
            val database = AppDatabase.getInstance(context)
            val preferences = UserPreferences.create(context)
            val dao = database.medicineDao()
            val savedList = dao.getAllMedicines().first()

            if (savedList.isEmpty()) {
                return Result.success()
            }

            if (BuildConfig.USE_DEMO) {
                // In demo mode, check if simulate alert was activated
                val isSimulated = preferences.isSimulateNewAlertEnabled.first()
                if (isSimulated) {
                    val telmisartan = dao.getMedicineByBatch("TEL2026B")
                    if (telmisartan != null && telmisartan.verdict != CheckVerdict.FLAGGED.name) {
                        dao.updateMedicine(telmisartan.copy(
                            verdict = CheckVerdict.FLAGGED.name,
                            citation = "CDSCO_NSQ_Oct2026.pdf · S.No 5 (Demo)"
                        ))
                        sendNotification(
                            medicineName = telmisartan.brand,
                            batch = telmisartan.batch,
                            verdict = CheckVerdict.FLAGGED
                        )
                    }
                }
            } else {
                // Remote mode: check version, then recheck items if changed
                val repo = RepositoryProvider.getRepository(context)
                val results = repo.recheckAll().getOrNull()
                results?.forEach { (medicine, checkResult) ->
                    if (medicine.verdict != checkResult.verdict && checkResult.verdict == CheckVerdict.FLAGGED) {
                        sendNotification(
                            medicineName = medicine.brand,
                            batch = medicine.batch,
                            verdict = checkResult.verdict
                        )
                    }
                }
            }

            Result.success()
        } catch (e: Exception) {
            Result.retry()
        }
    }

    private fun sendNotification(medicineName: String, batch: String, verdict: CheckVerdict) {
        createNotificationChannel()

        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }
        val pendingIntent = PendingIntent.getActivity(
            context,
            0,
            intent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val title = "Alert update for $medicineName"
        val message = "Batch $batch was identified in a newly published CDSCO quality alert."

        val builder = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.stat_notify_error)
            .setContentTitle(title)
            .setContentText(message)
            .setStyle(NotificationCompat.BigTextStyle().bigText(message))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)

        try {
            val notificationManager = NotificationManagerCompat.from(context)
            if (notificationManager.areNotificationsEnabled()) {
                notificationManager.notify(NOTIFICATION_ID_BASE + batch.hashCode(), builder.build())
            }
        } catch (_: SecurityException) {
            // Permission denied on Android 13+
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val name = context.getString(R.string.notification_channel_name)
            val descriptionText = context.getString(R.string.notification_channel_desc)
            val importance = NotificationManager.IMPORTANCE_HIGH
            val channel = NotificationChannel(CHANNEL_ID, name, importance).apply {
                description = descriptionText
            }
            val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }
}
