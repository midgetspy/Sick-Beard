/* -*- coding: iso-8859-1 -*-
 * ---------------------------------------------------------------------------
 * dvdinfo.py - parse dvd title structure
 * ---------------------------------------------------------------------------
 * $Id: ifomodule.c 3653 2008-10-26 18:52:55Z dmeyer $
 *
 * ---------------------------------------------------------------------------
 * kaa-Metadata - Media Metadata for Python
 * Copyright (C) 2003-2005 Thomas Schueppel, Dirk Meyer
 *
 * First Edition: Dirk Meyer <dmeyer@tzi.de>
 * Maintainer:    Dirk Meyer <dmeyer@tzi.de>
 *
 * based on http://arnfast.net/projects/ifoinfo.php by Jens Arnfast
 * and lsdvd by by Chris Phillips
 *
 * Please see the file AUTHORS for a complete list of authors.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of MER-
 * CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
 * Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
 *
 * ---------------------------------------------------------------------------
*/

#include <Python.h>

#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>
#include <string.h>
#include <unistd.h>
#include <assert.h>
#include <inttypes.h>
#include <stdint.h>

#include <dvdread/dvd_reader.h>
#include <dvdread/ifo_types.h>
#include <dvdread/ifo_read.h>

int dvdtime2msec(dvd_time_t *dt)
{
    static double frames_per_s[4] = {-1.0, 25.00, -1.0, 29.97};
    double fps = frames_per_s[(dt->frame_u & 0xc0) >> 6];
    long  ms;
    ms = (((dt->hour &   0xf0) >> 3) * 5 + (dt->hour   & 0x0f)) * 3600000;
    ms += (((dt->minute & 0xf0) >> 3) * 5 + (dt->minute & 0x0f)) * 60000;
    ms += (((dt->second & 0xf0) >> 3) * 5 + (dt->second & 0x0f)) * 1000;

    if(fps > 0)
        ms += ((dt->frame_u & 0x30) >> 3) * 5 + (dt->frame_u & 0x0f) * 1000.0 / fps;

    return ms;
}


static PyObject * ifoinfo_get_audio_track(ifo_handle_t *vtsfile, int ttn, int id) {
    char audioformat[7];
    char audiolang[5];
    int audiochannels;
    int audiofreq;
    int audioid;
    audio_attr_t *attr;
    pgc_t *pgc = vtsfile->vts_pgcit ? vtsfile->vts_pgcit->pgci_srp[ttn].pgc : NULL;

    if (!pgc || !vtsfile->vtsi_mat || (pgc->audio_control[id] & 0x8000) == 0)
        return NULL;

    attr = &vtsfile->vtsi_mat->vts_audio_attr[id];

    if ( attr->audio_format == 0
         && attr->multichannel_extension == 0
         && attr->lang_type == 0
         && attr->application_mode == 0
         && attr->quantization == 0
         && attr->sample_frequency == 0
         && attr->channels == 0
         && attr->lang_extension == 0
         && attr->unknown1 == 0
         && attr->unknown1 == 0) {
        return NULL;
    }

    audioid = pgc->audio_control[id] >> 8 & 7;

    /* audio format */
    switch (attr->audio_format) {
    case 0:
        snprintf(audioformat, 7, "0x2000");
        audioid += 128; // AC3 ids start at 128
        break;
    case 2:
        snprintf(audioformat, 7, "0x0050");
        break;
    case 3:
        snprintf(audioformat, 5, "MP2A");
        break;
    case 4:
        snprintf(audioformat, 7, "0x0001");
        audioid += 160; // PCM ids start at 160
        break;
    case 6:
        snprintf(audioformat, 7, "0x2001");
        audioid += 136; // DTS ids start at 136
        break;
    default:
        snprintf(audioformat, 7, "%02x%02x", 0, 0);
    }

    switch (attr->lang_type) {
    case 0:
        assert(attr->lang_code == 0 || attr->lang_code == 0xffff);
        snprintf(audiolang, 5, "N/A");
        break;
    case 1:
        snprintf(audiolang, 5, "%c%c", attr->lang_code>>8,
                 attr->lang_code & 0xff);
        break;
    default:
        snprintf(audiolang, 5, "N/A");
    }

    switch(attr->sample_frequency) {
    case 0:
        audiofreq = 48000;
        break;
    case 1:
        audiofreq = -1;
        break;
    default:
        audiofreq = -1;
    }

    audiochannels = attr->channels + 1;

    //AUDIOTRACK: ID=%i; LANG=%s; FORMAT=%s; CHANNELS=%i; FREQ=%ikHz
    return Py_BuildValue("(issii)", audioid, audiolang, audioformat, audiochannels, audiofreq);
}

static PyObject * ifoinfo_get_subtitle_track(ifo_handle_t *vtsfile, int ttn, int id) {
    int subid = id;
    char language[5];
    subp_attr_t *attr;
    video_attr_t *video = &vtsfile->vtsi_mat->vts_video_attr;
    pgc_t *pgc = vtsfile->vts_pgcit ? vtsfile->vts_pgcit->pgci_srp[ttn].pgc : NULL;

    if (!pgc || (pgc->subp_control[id] & 0x80000000) == 0)
        return NULL;

    attr = &vtsfile->vtsi_mat->vts_subp_attr[id];

    if ( attr->type == 0
         && attr->lang_code == 0
         && attr->zero1 == 0
         && attr->zero2 == 0
         && attr->lang_extension == 0 ) {
        return NULL;
    }

    if (video->display_aspect_ratio == 0) // 4:3
        subid = pgc->subp_control[id] >> 24 & 31;
    else if(video->display_aspect_ratio == 3) // 16:9
        subid = pgc->subp_control[id] >> 8 & 31;

    /* language code */
    if (isalpha((int)(attr->lang_code >> 8)) &&
        isalpha((int)(attr->lang_code & 0xff))) {
        snprintf(language, 5, "%c%c", attr->lang_code >> 8,
                 attr->lang_code & 0xff);
    } else {
        snprintf(language, 5, "%02x%02x",
                 0xff & (unsigned)(attr->lang_code >> 8),
                 0xff & (unsigned)(attr->lang_code & 0xff));
    }

    return Py_BuildValue("(is)", subid, language);
}

static PyObject *ifoinfo_read_title(dvd_reader_t *dvd, ifo_handle_t *ifofile,
                                    int id) {
    tt_srpt_t *tt_srpt;
    ifo_handle_t *vtsfile;
    video_attr_t *video_attr;
    int ttn;
    long playtime;
    int fps;
    PyObject *ret;
    PyObject *audio;
    PyObject *subtitles;
    PyObject *chapters;
    PyObject *tmp;
    int i;


    tt_srpt = ifofile->tt_srpt;
    Py_BEGIN_ALLOW_THREADS
    vtsfile = ifoOpen(dvd, tt_srpt->title[id].title_set_nr);
    Py_END_ALLOW_THREADS


    if (!vtsfile)
        return NULL;

    playtime = 0;
    ttn = tt_srpt->title[id].vts_ttn - 1;
    fps = 0;
    chapters = PyList_New(0);

    if (vtsfile->vts_pgcit) {
        dvd_time_t *time;
        pgc_t *pgc;
        i = vtsfile->vts_ptt_srpt->title[ttn].ptt[0].pgcn - 1;
        time = &vtsfile->vts_pgcit->pgci_srp[i].pgc->playback_time;
        fps = (time->frame_u & 0xc0) >> 6;
        playtime = dvdtime2msec(time);

        pgc = vtsfile->vts_pgcit->pgci_srp[i].pgc;
        int cell = 0;
        for (i = 0; i < pgc->nr_of_programs; i++) {
            int next = pgc->program_map[i + 1];
            int ms = 0;
            if (i == pgc->nr_of_programs - 1)
                next = pgc->nr_of_cells + 1;

            while (cell < next - 1) {
                ms += dvdtime2msec(&pgc->cell_playback[cell].playback_time);
                cell++;
            }
            tmp = PyFloat_FromDouble(ms / 1000.0);
            PyList_Append(chapters, tmp);
            Py_DECREF(tmp);
        }
    }

    audio = PyList_New(0);
    for (i=0; i < 8; i++) {
        tmp = ifoinfo_get_audio_track(vtsfile, ttn, i);
        if (!tmp)
            continue;
        PyList_Append(audio, tmp);
        Py_DECREF(tmp);
    }

    subtitles = PyList_New(0);
    for (i=0; i < 32; i++) {
        tmp = ifoinfo_get_subtitle_track(vtsfile, ttn, i);
        if (!tmp)
            continue;
        PyList_Append(subtitles, tmp);
        Py_DECREF(tmp);
    }

    video_attr = &vtsfile->vtsi_mat->vts_video_attr;

    /* chapters, angles, playtime, fps, format, aspect, width, height, audio,
       subtitles */
    ret = Py_BuildValue("(OidiiiiiOO)",
                        chapters,
                        tt_srpt->title[id].nr_of_angles,
                        playtime / 1000.0,

                        fps,
                        video_attr->video_format,
                        video_attr->display_aspect_ratio,

                        video_attr->picture_size,
                        video_attr->video_format,
                        audio,
                        subtitles);
    ifoClose(vtsfile);
    return ret;
}


static PyObject *ifoinfo_parse(PyObject *self, PyObject *args) {
    char *dvddevice;
    dvd_reader_t *dvd;
    ifo_handle_t *ifofile;
    PyObject *ret;
    int i;

    if (!PyArg_ParseTuple(args, "s", &dvddevice))
        return Py_BuildValue("i", 0);

    Py_BEGIN_ALLOW_THREADS
    dvd = DVDOpen(dvddevice);
    Py_END_ALLOW_THREADS

    if (!dvd) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    Py_BEGIN_ALLOW_THREADS
    ifofile = ifoOpen(dvd, 0);
    Py_END_ALLOW_THREADS

    if (!ifofile) {
        DVDClose(dvd);
        Py_INCREF(Py_None);
        return Py_None;
    }

    ret = PyList_New(0);

    for (i=0; i<ifofile->tt_srpt->nr_of_srpts; i++) {
        PyObject *title = ifoinfo_read_title(dvd, ifofile, i);
        if (!title)
            break;
        PyList_Append(ret, title);
        Py_DECREF(title);
    }

    /* close */
    ifoClose(ifofile);
    DVDClose(dvd);
    return ret;

}


static PyMethodDef IfoMethods[] = {
    {"parse",  ifoinfo_parse, METH_VARARGS},
    {NULL, NULL}
};


void init_ifoparser(void) {
    (void) Py_InitModule("_ifoparser", IfoMethods);
    PyEval_InitThreads();
}
