package com.penguinoo.codexmobile;

import android.content.Context;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ArrayAdapter;
import android.widget.TextView;

import androidx.core.content.ContextCompat;

import java.util.List;

final class ReadableSpinnerAdapter extends ArrayAdapter<String> {
    ReadableSpinnerAdapter(Context context, List<String> values) {
        super(context, android.R.layout.simple_spinner_item, values);
    }

    @Override
    public View getView(int position, View convertView, ViewGroup parent) {
        TextView view = (TextView) super.getView(position, convertView, parent);
        styleText(view, false);
        return view;
    }

    @Override
    public View getDropDownView(int position, View convertView, ViewGroup parent) {
        TextView view = (TextView) super.getDropDownView(position, convertView, parent);
        styleText(view, true);
        return view;
    }

    private void styleText(TextView view, boolean dropdown) {
        Context context = getContext();
        view.setTextColor(ContextCompat.getColor(context, R.color.text_main));
        view.setTextSize(15f);
        view.setPadding(dp(12), dp(12), dp(12), dp(12));
        view.setBackgroundColor(ContextCompat.getColor(
                context,
                dropdown ? R.color.dialog_surface_alt : R.color.dialog_surface
        ));
    }

    private int dp(int value) {
        return Math.round(value * getContext().getResources().getDisplayMetrics().density);
    }
}
